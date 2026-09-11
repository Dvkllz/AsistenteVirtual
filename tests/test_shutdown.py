"""Exercise the real Qt event loop in a separate process, without network."""

import os
from pathlib import Path
import subprocess
import sys
import unittest


class ShutdownTests(unittest.TestCase):
    def test_real_close_audio_finishes_before_exit_with_or_without_worker(self):
        for worker_delay in (None, .05, 1.8):
            with self.subTest(worker_delay=worker_delay):
                source = '''
import time
from tempfile import TemporaryDirectory
from PyQt6.QtCore import QTimer, QSettings
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtWidgets import QApplication
from desktop_pet.window import PetWindow
app = QApplication([])
test_settings = TemporaryDirectory()
settings = QSettings(test_settings.name + '/settings.ini', QSettings.Format.IniFormat)
settings.setValue('physics/enabled', False)
settings.setValue('autonomy/enabled', False)
worker_delay = WORKER_DELAY
window = PetWindow(responder=lambda q: (time.sleep(worker_delay or 0), 'Listo')[1],
                   settings=settings)
for output in window.sounds.outputs.values():
    output.setMuted(True)
ended = []
window.sounds.players['close'].mediaStatusChanged.connect(
    lambda status: ended.append(True) if status == QMediaPlayer.MediaStatus.EndOfMedia else None)
window.show()
if worker_delay is not None:
    window.input.setText('Hola')
    window.submit()
QTimer.singleShot(20, window.close)
QTimer.singleShot(6000, lambda: app.exit(9))
result = app.exec()
assert result == 0, result
assert ended, 'Exit cut the close audio short'
assert window.worker is None, 'Exited before HTTP worker finished'
assert not window._close_sound_pending
'''.replace('WORKER_DELAY', repr(worker_delay))
                env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
                result = subprocess.run([sys.executable, '-c', source],
                                        cwd=Path(__file__).resolve().parent.parent,
                                        env=env, capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_close_during_answer_exits_process(self):
        source = '''
import time
from tempfile import TemporaryDirectory
from PyQt6.QtCore import QTimer, QSettings
from PyQt6.QtWidgets import QApplication
from desktop_pet.window import PetWindow
app = QApplication([])
test_settings = TemporaryDirectory()
settings = QSettings(test_settings.name + '/settings.ini', QSettings.Format.IniFormat)
settings.setValue('sound/effects', False)
window = PetWindow(responder=lambda q: (time.sleep(0.2), "Listo")[1], settings=settings)
window.show()
window.input.setText("Hola")
window.submit()
QTimer.singleShot(10, window.close)
QTimer.singleShot(3000, lambda: app.exit(9))
raise SystemExit(app.exec())
'''
        env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
        result = subprocess.run([sys.executable, '-c', source],
                                cwd=Path(__file__).resolve().parent.parent,
                                env=env, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
