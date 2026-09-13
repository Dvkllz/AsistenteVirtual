"""Local MP3 purr, looped only while petting; never opens a microphone."""

from pathlib import Path
from PyQt6.QtCore import QUrl
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer

PURR_PATH = Path(__file__).resolve().parent.parent / "assets/audio/ronroneo.mp3"


class PurrSound:
    def __init__(self, parent, enabled=True):
        self.enabled = enabled
        self.wanted = False
        self.loaded = False
        self.output = QAudioOutput(parent)
        self.output.setVolume(.4)
        self.effect = QMediaPlayer(parent)
        self.effect.setAudioOutput(self.output)
        self.effect.setLoops(QMediaPlayer.Loops.Infinite.value)

    def is_playing(self):
        return self.effect.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def start(self):
        self.wanted = self.enabled
        if not self.wanted or self.is_playing():
            return
        if not self.loaded:
            if not PURR_PATH.is_file():
                return
            self.loaded = True
            self.effect.setSource(QUrl.fromLocalFile(str(PURR_PATH)))
        self.effect.play()

    def stop(self):
        self.wanted = False
        self.effect.stop()

    def set_enabled(self, enabled):
        self.enabled = enabled
        if not enabled:
            self.stop()
