"""Local meows and MP3 effects. Playback never blocks the GUI thread."""

from pathlib import Path
import random
from PyQt6.QtCore import QObject, QTimer, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer

AUDIO_DIR = Path(__file__).resolve().parent.parent / "assets/audio"
MEOWS = ("meow_1", "meow_2", "meow_3")
FILES = {**{name: name + ".wav" for name in MEOWS},
         "close": "explota.mp3", "walk": "caminar1.mp3"}


class CatSounds(QObject):
    close_finished = pyqtSignal()

    def __init__(self, parent=None, *, enabled=True):
        super().__init__(parent)
        self.enabled = enabled
        self.walking = False
        self.speaking = False
        self.last_meow = None
        self.rng = random.Random()
        self.closing = False
        self.close_pending = False
        self.players = {}
        self.outputs = {}
        self.loaded = set()
        for name, filename in FILES.items():
            output = QAudioOutput(self)
            output.setVolume(.35)
            player = QMediaPlayer(self)
            player.setAudioOutput(output)
            player.setLoops(QMediaPlayer.Loops.Infinite.value if name == "walk" else 1)
            self.players[name] = player
            self.outputs[name] = output
        self.players["close"].mediaStatusChanged.connect(self._close_status)
        self.players["close"].errorOccurred.connect(lambda *_: self._finish_close())
        self.close_timeout = QTimer(self)
        self.close_timeout.setSingleShot(True)
        self.close_timeout.timeout.connect(self._finish_close)

    def _play(self, name):
        player = self.players[name]
        if name not in self.loaded:
            self.loaded.add(name)
            player.setSource(QUrl.fromLocalFile(str(AUDIO_DIR / FILES[name])))
        player.setPosition(0)
        player.play()

    def start_speech(self):
        if self.closing:
            return
        self.speaking = True
        for name in MEOWS:
            self.players[name].stop()
        if self.enabled:
            self.last_meow = self.rng.choice([name for name in MEOWS if name != self.last_meow])
            self._play(self.last_meow)

    def stop_speech(self, *, completed=False):
        self.speaking = False
        # A one-shot meow may finish naturally; never start an end-of-dialogue sound.
        if not completed:
            for name in MEOWS:
                self.players[name].stop()

    def set_walking(self, walking):
        walking = bool(walking and not self.closing)
        if walking == self.walking:
            return
        self.walking = walking
        if walking and self.enabled:
            self._play("walk")
        else:
            self.players["walk"].stop()

    def set_enabled(self, enabled):
        self.enabled = enabled
        if not enabled:
            for player in self.players.values():
                player.stop()
            if self.close_pending:
                self._finish_close()
        elif not self.closing:
            if self.walking:
                self._play("walk")

    def begin_close(self):
        if self.closing:
            return self.close_pending
        self.closing = True
        self.walking = self.speaking = False
        for player in self.players.values():
            player.stop()
        if (not self.enabled or not (AUDIO_DIR / FILES["close"]).is_file()
                or self.players["close"].error() != QMediaPlayer.Error.NoError):
            return False
        self.close_pending = True
        # Bound shutdown even if the decoder/device never reports completion.
        self.close_timeout.start(10000)
        self._play("close")
        return self.close_pending

    def _close_status(self, status):
        if status in (QMediaPlayer.MediaStatus.EndOfMedia, QMediaPlayer.MediaStatus.InvalidMedia):
            self._finish_close()

    def _finish_close(self):
        if not self.close_pending:
            return
        self.close_pending = False
        self.close_timeout.stop()
        self.players["close"].stop()
        self.close_finished.emit()
