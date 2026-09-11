"""Local, non-blocking purr. Missing audio devices never block petting."""

from pathlib import Path
from PyQt6.QtCore import QUrl
from PyQt6.QtMultimedia import QSoundEffect

PURR_PATH = Path(__file__).resolve().parent.parent / 'assets/audio/purr.wav'


class PurrSound:
    def __init__(self, parent, enabled=True):
        self.enabled = enabled
        self.wanted = False
        self.effect = QSoundEffect(parent)
        self.effect.setLoopCount(QSoundEffect.Loop.Infinite.value)
        self.effect.setVolume(.18)
        self.effect.statusChanged.connect(self._ready)
        self.effect.setSource(QUrl.fromLocalFile(str(PURR_PATH)))

    def _ready(self):
        if (self.wanted and self.enabled and self.effect.status() == QSoundEffect.Status.Ready
                and not self.effect.isPlaying()):
            self.effect.play()

    def start(self):
        self.wanted = self.enabled
        self._ready()

    def stop(self):
        self.wanted = False
        self.effect.stop()

    def set_enabled(self, enabled):
        self.enabled = enabled
        if not enabled:
            self.stop()
